#[no_mangle]
pub extern "C" fn FOO() {
    // Correctly defined as a function to match the extern declaration
}

fn main() {
    extern "C" {
        fn FOO();
    }
    unsafe {
        // Now FOO refers to a valid function symbol instead of a static variable
        FOO()
    }
}