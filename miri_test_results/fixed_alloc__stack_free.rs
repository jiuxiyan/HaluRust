fn main() {
    let x = 42;
    // Correctly allocate on the heap and copy the value of x
    let good_box = Box::new(x);
    // good_box will be safely deallocated here or via explicit drop
    drop(good_box);
}