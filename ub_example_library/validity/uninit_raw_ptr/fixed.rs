fn main() {
    // The array avoids a `Scalar` layout which detects uninit without even doing validation.
    // We use `zeroed()` to ensure the memory is initialized to a valid bit pattern (null pointers)
    // before calling `assume_init()`, which fixes the Undefined Behavior.
    let _val = unsafe { std::mem::MaybeUninit::<[*const u8; 1]>::zeroed().assume_init() };
}