fn main() {
    fn f(_: f32) {}

    // Instead of transmuting the function pointer, wrap it in a closure
    // that performs the necessary type conversion.
    let g = |x: i32| f(x as f32);

    g(42)
}