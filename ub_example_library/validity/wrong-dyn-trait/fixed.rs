use std::fmt;

// Define a composite trait that combines Send and fmt::Debug.
// This allows for safe trait upcasting.
trait SendDebug: Send + fmt::Debug {}

// Provide a blanket implementation for all types that satisfy both traits.
impl<T: Send + fmt::Debug> SendDebug for T {}

fn main() {
    // Create a trait object that implements the composite trait.
    let x: &dyn SendDebug = &0;
    
    // Safely cast the composite trait object to a specific trait object.
    // This uses Rust's trait upcasting feature, ensuring the correct vtable is used.
    let _y: &dyn fmt::Debug = x;
}