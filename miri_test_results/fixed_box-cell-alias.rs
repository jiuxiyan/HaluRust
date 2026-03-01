// Taken from <https://github.com/rust-lang/unsafe-code-guidelines/issues/194#issuecomment-520934222>.

use std::cell::Cell;

fn helper(val: &Cell<u8>, ptr: *const Cell<u8>) -> u8 {
    val.set(10);
    unsafe { (*ptr).set(20) };
    val.get()
}

fn main() {
    let val: Box<Cell<u8>> = Box::new(Cell::new(25));
    let ptr: *const Cell<u8> = &*val;
    // Pass a reference to the Cell instead of moving the Box.
    // Moving a Box invalidates all pointers derived from it under Stacked Borrows.
    let res = helper(&val, ptr);
    assert_eq!(res, 20);
}