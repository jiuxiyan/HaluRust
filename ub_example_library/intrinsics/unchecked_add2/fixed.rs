fn main() {
    // MIN overflow - fixed by using wrapping_add to avoid Undefined Behavior
    let _val = (-30000i16).wrapping_add(-8000);
}