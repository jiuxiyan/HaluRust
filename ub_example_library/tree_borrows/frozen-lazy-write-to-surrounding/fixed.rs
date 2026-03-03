fn main() {
    // 1. Make the pair mutable to allow mutation of its fields.
    let mut pair = ((), 1);
    
    // 2. Obtain a mutable raw pointer directly to the field we want to mutate.
    // This ensures correct provenance and write permissions for the i32 memory.
    let ptr = &raw mut pair.1;
    
    // 3. Perform the write safely (within unsafe block)
    unsafe {
        ptr.write(0);
    }
    
    assert_eq!(pair.1, 0);
}