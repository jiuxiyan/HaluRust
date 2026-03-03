fn main() {
    let mut x = 0;
    // To allow writing through a pointer reconstructed from an address,
    // the provenance must be exposed from a mutable pointer.
    let addr = (&mut x as *mut i32).expose_provenance();
    let ptr = std::ptr::with_exposed_provenance_mut::<i32>(addr);
    unsafe { *ptr = 0 };
}