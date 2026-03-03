use std::cell::Cell;

// Use shared references to Cell to allow safe aliasing with mutation.
// This avoids the Undefined Behavior caused by mixing &mut and & aliases.
fn retarget<'a>(x: &mut &'a Cell<u32>, target: &'a Cell<u32>) {
    // No unsafe needed: Cell allows shared references to be copied/assigned
    // while still permitting mutation of the interior value.
    *x = target;
}

fn main() {
    // Use Cell for interior mutability.
    let target = Cell::new(42);
    let dummy = Cell::new(42); // initial dummy value
    let mut target_alias = &dummy; 

    // Pass shared references to the Cell.
    retarget(&mut target_alias, &target);
    
    // now `target_alias` points to the same thing as `target`
    // Mutation via Cell is safe even if aliases exist.
    target.set(13);
    
    // Reading via the alias is now valid and safe under Rust's memory model.
    let _val = target_alias.get();
}