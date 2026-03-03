fn main() {
    // The 'as' operator in Rust performs a saturating conversion for float-to-int.
    // This is safe and well-defined: f32::INFINITY as i32 will result in i32::MAX.
    let _val = f32::INFINITY as i32;
}