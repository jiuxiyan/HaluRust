unsafe extern "C" fn helper(_: i32, _: i64) {}

fn main() {
    unsafe {
        let f = helper as *const ();
        let f = std::mem::transmute::<_, unsafe extern "C" fn(i32, i64)>(f);

        f(1i32, 1i64);
    }
}