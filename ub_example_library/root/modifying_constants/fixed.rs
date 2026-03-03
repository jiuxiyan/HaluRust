fn main() {
    // Store the value in a mutable variable on the stack to avoid constant promotion to read-only memory
    let mut x = 1;
    
    // Use a standard mutable reference to modify the value
    let y = &mut x;
    *y = 42;
    
    // Verify the change
    assert_eq!(x, 42);
}