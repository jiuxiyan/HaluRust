fn main() {
    unsafe {
        let mut root = 6u8;
        let mref = &mut root;
        let ptr = mref as *mut u8;
        *ptr = 0; // Write
        
        // Access the value through the pointer instead of the owner 'root'.
        // Reading from 'root' directly would be a foreign read that freezes 
        // the mutable borrow, preventing further writes through 'ptr'.
        assert_eq!(*ptr, 0); 
        
        *ptr = 0;
    }
}