fn main() {
    // Correctly represent a nullable function pointer using Option
    let b: Option<fn()> = unsafe { std::mem::transmute(0usize) };
    
    // Check for nullity safely
    if let Some(func) = b {
        func();
    } else {
        println!("Function pointer was null (None)");
    }
}