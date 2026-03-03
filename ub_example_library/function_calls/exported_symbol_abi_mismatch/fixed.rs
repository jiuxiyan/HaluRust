#[no_mangle]
extern "C" fn foo() {}

fn main() {
    #[cfg(any(cache, fn_ptr))]
    extern "C" {
        fn foo();
    }

    #[cfg(fn_ptr)]
    unsafe {
        // Ensure the transmute source type matches the definition's ABI (extern "C").
        std::mem::transmute::<unsafe extern "C" fn(), unsafe extern "C" fn()>(foo)();
    }

    // `Instance` caching should not suppress ABI check.
    #[cfg(cache)]
    unsafe {
        foo();
    }

    {
        #[cfg_attr(any(cache, fn_ptr), allow(clashing_extern_declarations))]
        extern "C" {
            fn foo();
        }
        unsafe {
            // Now the definition of foo (extern "C") matches this declaration.
            foo();
        }
    }
}