fn main() {
    let x: i32 = 3;
    let x_ptr = &x as *const i32;

    // Use expose_provenance() to explicitly mark the pointer's provenance as exposed.
    // This allows with_exposed_provenance to reconstruct a valid pointer later.
    let x_usize: usize = x_ptr.expose_provenance();
    
    // Cast back an address that has been exposed.
    let ptr = std::ptr::with_exposed_provenance::<i32>(x_usize);
    assert_eq!(unsafe { *ptr }, 3);
}