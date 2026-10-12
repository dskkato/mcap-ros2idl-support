use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict, PyList, PyString};
use pyo3::IntoPyObjectExt;
use std::collections::HashMap;

type FieldInput = (String, String, usize, i64, HashMap<i64, String>);
type PlanInput = (
    bool,
    String,
    Vec<FieldInput>,
    Vec<(Vec<i64>, FieldInput)>,
    Option<FieldInput>,
    HashMap<i64, String>,
);
struct Field {
    name: Py<PyString>,
    kind: String,
    target: usize,
    count: i64,
    mapping: HashMap<i64, Py<PyString>>,
}
struct Plan {
    union: bool,
    switch: String,
    fields: Vec<Field>,
    cases: Vec<(Vec<i64>, Field)>,
    default: Option<Field>,
    mapping: HashMap<i64, Py<PyString>>,
}
fn mapping(py: Python<'_>, m: HashMap<i64, String>) -> HashMap<i64, Py<PyString>> {
    m.into_iter()
        .map(|(k, v)| (k, PyString::intern(py, &v).unbind()))
        .collect()
}
fn field(py: Python<'_>, f: FieldInput) -> Field {
    Field {
        name: PyString::intern(py, &f.0).unbind(),
        kind: f.1,
        target: f.2,
        count: f.3,
        mapping: mapping(py, f.4),
    }
}
#[pyclass]
struct Decoder {
    plans: Vec<Plan>,
    root: usize,
    ros1: bool,
    byte_arrays: bool,
}
#[pymethods]
impl Decoder {
    #[new]
    fn new(
        py: Python<'_>,
        inputs: Vec<PlanInput>,
        root: usize,
        ros1: bool,
        byte_arrays: bool,
    ) -> PyResult<Self> {
        let plans: Vec<_> = inputs
            .into_iter()
            .map(|p| Plan {
                union: p.0,
                switch: p.1,
                fields: p.2.into_iter().map(|f| field(py, f)).collect(),
                cases: p.3.into_iter().map(|(v, f)| (v, field(py, f))).collect(),
                default: p.4.map(|f| field(py, f)),
                mapping: mapping(py, p.5),
            })
            .collect();
        if root >= plans.len() {
            return Err(PyValueError::new_err("Invalid root definition"));
        }
        for p in &plans {
            for f in p
                .fields
                .iter()
                .chain(p.cases.iter().map(|c| &c.1))
                .chain(p.default.iter())
            {
                if f.kind == "complex" && f.target >= plans.len() {
                    return Err(PyValueError::new_err("Invalid nested definition"));
                }
            }
        }
        Ok(Self {
            plans,
            root,
            ros1,
            byte_arrays,
        })
    }
    fn read_message(&self, py: Python<'_>, data: &[u8]) -> PyResult<PyObject> {
        let mut r = Reader::new(data)?;
        self.read_plan(py, self.root, &mut r, 0)
    }
}
struct Reader<'a> {
    data: &'a [u8],
    offset: usize,
    little: bool,
    align8: usize,
}
impl<'a> Reader<'a> {
    fn new(data: &'a [u8]) -> PyResult<Self> {
        if data.len() < 4 {
            return Err(PyValueError::new_err("CDR requires a 4-byte header"));
        }
        let kind = data[1];
        // Parameter-list and delimited encodings require schema extensibility metadata.
        if !matches!(kind, 0 | 1 | 6 | 7 | 16 | 17) || data[0] != 0 {
            return Err(PyValueError::new_err(format!(
                "Unsupported CDR encapsulation: {}",
                kind
            )));
        }
        Ok(Self {
            data,
            offset: 4,
            little: kind & 1 != 0,
            align8: if kind > 3 { 4 } else { 8 },
        })
    }
    fn take(&mut self, n: usize, alignment: usize) -> PyResult<&'a [u8]> {
        let padding = (alignment - (self.offset - 4) % alignment) % alignment;
        let start = self
            .offset
            .checked_add(padding)
            .ok_or_else(|| PyValueError::new_err("CDR offset overflow"))?;
        let end = start
            .checked_add(n)
            .ok_or_else(|| PyValueError::new_err("CDR length overflow"))?;
        let value = self.data.get(start..end).ok_or_else(|| {
            PyValueError::new_err(format!(
                "Truncated CDR payload at offset {start}: need {n} bytes"
            ))
        })?;
        self.offset = end;
        Ok(value)
    }
    fn number(&mut self, n: usize) -> PyResult<u64> {
        let a = if n == 8 { self.align8 } else { n };
        let little = self.little;
        let bytes = self.take(n, a)?;
        let mut value = 0u64;
        if little {
            for (i, b) in bytes.iter().enumerate() {
                value |= (*b as u64) << (8 * i);
            }
        } else {
            for b in bytes {
                value = (value << 8) | *b as u64;
            }
        }
        Ok(value)
    }
}
impl Decoder {
    fn primitive(&self, py: Python<'_>, kind: &str, r: &mut Reader<'_>) -> PyResult<PyObject> {
        macro_rules! value {
            ($v:expr) => {
                $v.into_py_any(py)
            };
        }
        match kind {
            "bool" => value!(r.number(1)? != 0),
            "uint8" => value!(r.number(1)? as u8),
            "int8" => value!(r.number(1)? as i8),
            "uint16" => value!(r.number(2)? as u16),
            "int16" => value!(r.number(2)? as i16),
            "uint32" => value!(r.number(4)? as u32),
            "int32" => value!(r.number(4)? as i32),
            "uint64" => value!(r.number(8)?),
            "int64" => value!(r.number(8)? as i64),
            "float32" => value!(f32::from_bits(r.number(4)? as u32)),
            "float64" => value!(f64::from_bits(r.number(8)?)),
            "string" => {
                let n = r.number(4)? as usize;
                let bytes = r.take(n, 1)?;
                let text = std::str::from_utf8(if n > 0 { &bytes[..n - 1] } else { bytes })
                    .map_err(|e| PyValueError::new_err(format!("Invalid CDR UTF-8: {e}")))?;
                value!(text)
            }
            "time" | "duration" => {
                let d = PyDict::new(py);
                d.set_item("sec", r.number(4)? as i32)?;
                d.set_item(
                    if self.ros1 { "nsec" } else { "nanosec" },
                    r.number(4)? as u32,
                )?;
                Ok(d.into_any().unbind())
            }
            "wstring" => Err(PyRuntimeError::new_err(
                "wstring is implementation-defined and therefore not supported",
            )),
            _ => Err(PyValueError::new_err(format!(
                "Unrecognized primitive type {kind}"
            ))),
        }
    }
    fn read_field(
        &self,
        py: Python<'_>,
        f: &Field,
        r: &mut Reader<'_>,
        depth: usize,
    ) -> PyResult<PyObject> {
        if f.kind == "wstring" {
            return Err(PyRuntimeError::new_err(
                "wstring is implementation-defined and therefore not supported",
            ));
        }
        let one = |r: &mut Reader<'_>| -> PyResult<PyObject> {
            let value = if f.kind == "complex" {
                self.read_plan(py, f.target, r, depth + 1)?
            } else {
                self.primitive(py, &f.kind, r)?
            };
            if !f.mapping.is_empty() {
                if let Ok(n) = value.extract::<i64>(py) {
                    if let Some(s) = f.mapping.get(&n) {
                        return Ok(s.clone_ref(py).into_any());
                    }
                }
            }
            Ok(value)
        };
        if f.count == -1 {
            return one(r);
        }
        let count = if f.count == -2 {
            r.number(4)? as usize
        } else {
            f.count as usize
        };
        // Every supported element consumes at least one byte. Check before allocating.
        if count > r.data.len().saturating_sub(r.offset) {
            return Err(PyValueError::new_err(
                "Array length exceeds remaining CDR payload",
            ));
        }
        if self.byte_arrays && f.kind == "uint8" && f.mapping.is_empty() {
            return Ok(PyBytes::new(py, r.take(count, 1)?).into_any().unbind());
        }
        if count == 0 {
            return Ok(PyList::empty(py).into_any().unbind());
        }
        if f.mapping.is_empty() {
            let width = match f.kind.as_str() {
                "bool" | "uint8" | "int8" => 1,
                "uint16" | "int16" => 2,
                "uint32" | "int32" | "float32" => 4,
                "uint64" | "int64" | "float64" => 8,
                _ => 0,
            };
            if width > 0 {
                let little = r.little;
                let size = count
                    .checked_mul(width)
                    .ok_or_else(|| PyValueError::new_err("CDR array length overflow"))?;
                let alignment = if width == 8 { r.align8 } else { width };
                let bytes = r.take(size, alignment)?;
                macro_rules! array {
                    ($ty:ty, $width:expr) => {{
                        let values = bytes.chunks_exact($width).map(|b| {
                            let raw = b.try_into().expect("chunks_exact guarantees element width");
                            if little {
                                <$ty>::from_le_bytes(raw)
                            } else {
                                <$ty>::from_be_bytes(raw)
                            }
                        });
                        return Ok(PyList::new(py, values)?.into_any().unbind());
                    }};
                }
                match f.kind.as_str() {
                    "bool" => {
                        return Ok(PyList::new(py, bytes.iter().map(|b| *b != 0))?
                            .into_any()
                            .unbind())
                    }
                    "uint8" => {
                        return Ok(PyList::new(py, bytes.iter().copied())?.into_any().unbind())
                    }
                    "int8" => {
                        return Ok(PyList::new(py, bytes.iter().map(|b| *b as i8))?
                            .into_any()
                            .unbind())
                    }
                    "uint16" => array!(u16, 2),
                    "int16" => array!(i16, 2),
                    "uint32" => array!(u32, 4),
                    "int32" => array!(i32, 4),
                    "uint64" => array!(u64, 8),
                    "int64" => array!(i64, 8),
                    "float32" => array!(f32, 4),
                    "float64" => array!(f64, 8),
                    _ => unreachable!(),
                }
            }
        }
        let mut values = Vec::with_capacity(count);
        for _ in 0..count {
            values.push(one(r)?);
        }
        Ok(PyList::new(py, values)?.into_any().unbind())
    }
    fn read_plan(
        &self,
        py: Python<'_>,
        index: usize,
        r: &mut Reader<'_>,
        depth: usize,
    ) -> PyResult<PyObject> {
        if depth > 128 {
            return Err(PyValueError::new_err("CDR nesting exceeds 128 levels"));
        }
        let p = &self.plans[index];
        let d = PyDict::new(py);
        if p.union {
            let discr = self.primitive(py, &p.switch, r)?;
            let n = discr.extract::<i64>(py)?;
            if let Some(s) = p.mapping.get(&n) {
                d.set_item("discriminator", s.bind(py))?;
            } else {
                d.set_item("discriminator", discr)?;
            }
            let f = p
                .cases
                .iter()
                .find(|(v, _)| v.contains(&n))
                .map(|c| &c.1)
                .or(p.default.as_ref())
                .ok_or_else(|| {
                    PyValueError::new_err(format!("No union field matches discriminant {n}"))
                })?;
            d.set_item(f.name.bind(py), self.read_field(py, f, r, depth)?)?;
        } else if p.fields.is_empty() {
            r.number(1)?;
        } else {
            for f in &p.fields {
                d.set_item(f.name.bind(py), self.read_field(py, f, r, depth)?)?;
            }
        }
        Ok(d.into_any().unbind())
    }
}
#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Decoder>()
}
