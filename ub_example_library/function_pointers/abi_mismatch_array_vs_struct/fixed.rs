#![feature(portable_simd)]

// Some targets treat arrays and structs very differently. We would probably catch that on those
// targets since we check the `PassMode`; here we ensure that we catch it on *all* targets
// (in particular, on x86-64 the pass mode is `Indirect` for both of these).
struct S(
    #[allow(dead_code)] i32,
    #[allow(dead_code)] i32,
    #[allow(dead_code)] i32,
    #[allow(dead_code)] i32,
);
type A = [i32; 4];

fn main() {
    fn f(_: S) {}

    // These two types have the same size but are still not compatible.
    // Instead of transmuting the function pointer, which is UB, we use a wrapper
    // that performs the conversion from the array to the struct.
    let g = |arr: A| {
        let s = S(arr[0], arr[1], arr[2], arr[3]);
        f(s)
    };

    g(Default::default())
}