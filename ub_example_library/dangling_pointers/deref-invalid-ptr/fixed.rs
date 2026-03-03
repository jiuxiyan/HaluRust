// This should fail even without validation.

fn main() {
    let x = 16usize as *const u32;
    // To avoid Undefined Behavior, we avoid creating a reference (&*x).
    // Instead, we work directly with the raw pointer.
    let _y = x;
}