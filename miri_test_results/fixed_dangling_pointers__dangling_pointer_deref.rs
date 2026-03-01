// Make sure we find these even with many checks disabled.

fn main() {
    let x = {
        let b = Box::new(42);
        *b // Dereference the box to get the i32 value
    };
    // x is now 42, and the Box was dropped after the value was copied out
    println!("The value is: {}", x);
}