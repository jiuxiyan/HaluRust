fn main() {
    let mut x = 0;
    x = 1;
    let y: *const i32 = &x;

    assert_eq!(unsafe { *y }, 1);

    assert_eq!(x, 1);
}