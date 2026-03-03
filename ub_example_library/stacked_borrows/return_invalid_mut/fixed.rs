// Make sure that we cannot return a `&mut` that got already invalidated.
fn foo(x: &mut (i32, i32)) -> &mut i32 {
    // If we need to read the value, we must do it before borrowing a field mutably.
    // Reading through the original reference is safe here.
    let _val = *x; 
    
    // Safe field projection: this correctly handles the borrow stack.
    &mut x.1
}

fn main() {
    let mut data = (1, 2);
    foo(&mut data);
}