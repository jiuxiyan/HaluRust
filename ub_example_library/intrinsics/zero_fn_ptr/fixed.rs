fn main() {
    // Safely initialize a nullable function pointer as 'None' (null).
    // Rust's Null Pointer Optimization (NPO) ensures Option<fn()> 
    // has the same size as fn() and uses null to represent None.
    let _f: Option<fn()> = None;
}