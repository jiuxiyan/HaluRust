fn main() {
    let val = 0;
    let ptr = &val as *const i32;
    
    // Get the address as a usize without losing provenance context
    let addr = ptr.addr();
    
    // Reconstruct the pointer by applying the address back to the original pointer (preserving provenance)
    let _ptr = ptr.with_addr(addr);
}