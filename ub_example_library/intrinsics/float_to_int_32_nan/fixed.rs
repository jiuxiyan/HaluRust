fn main() {
    // The 'as' operator is safe and performs a saturating cast.
    // NaN will result in 0.
    let val: u32 = f32::NAN as u32;
    println!("{}", val);
}