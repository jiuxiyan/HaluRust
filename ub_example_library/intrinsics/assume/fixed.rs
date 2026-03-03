fn main() {
    let x = 5;
    // Use standard assertions for runtime checks.
    // These are safe and prevent Undefined Behavior.
    assert!(x < 10);
    assert!(x > 1);
    assert!(x < 42);
}