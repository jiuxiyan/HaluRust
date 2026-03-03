fn main() {
    // Move the value to the outer scope so it lives long enough
    let val: u32 = 42;

    // Create the intermediate reference in the outer scope
    // This ensures the reference itself has a valid memory location
    let val_ref: &u32 = &val;

    // Create the double reference safely
    let x: &&u32 = &val_ref;

    let _ = || {
        match x {
            &&_y => {}
        }
    };
}