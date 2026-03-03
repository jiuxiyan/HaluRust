use std::cell::RefCell;

fn main() {
    // x does not need to be &mut for RefCell interior mutability
    let x = RefCell::new(0);
    
    // 1. Perform the mutation. 
    // This is safe because no other borrows are active.
    x.replace(1);
    
    // 2. Borrow the data after the mutation to read the new value.
    // The Ref guard ensures safety and correct aliasing.
    let borrow = x.borrow();
    let y: &i32 = &*borrow;
    
    let _val = *y;
    assert_eq!(_val, 1);
}