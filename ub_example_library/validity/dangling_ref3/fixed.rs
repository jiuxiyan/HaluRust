// Use a static to ensure the memory lives for the duration of the program
static DATA: i32 = 0;

fn dangling() -> *const i32 {
    &DATA as *const i32
}

fn main() {
    // Safety: dangling() returns a pointer to static memory, 
    // which is always valid and properly aligned for i32.
    // We use dereferencing (&*) instead of transmute for better type safety.
    let _x: &i32 = unsafe { &*dangling() };
    
    // Verify the value is accessible
    assert_eq!(*_x, 0);
}