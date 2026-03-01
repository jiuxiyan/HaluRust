use std::cell::RefCell;
use std::rc::{Rc, Weak};

// Define a Weak version of the Dummy struct to break the reference cycle.
struct WeakDummy(Weak<RefCell<Option<WeakDummy>>>);

// Modify Dummy to store the Weak version of itself.
struct Dummy(Rc<RefCell<Option<WeakDummy>>>);

fn main() {
    // Create the initial Dummy instance.
    let x = Dummy(Rc::new(RefCell::new(None)));
    
    // Create y as a clone of the Rc inside x.
    let y = Dummy(x.0.clone());
    
    // Downgrade the strong Rc in y to a Weak pointer before storing it.
    // This prevents a strong reference cycle that would cause a memory leak.
    let weak_y = WeakDummy(Rc::downgrade(&y.0));
    
    // Store the weak reference inside the RefCell.
    *x.0.borrow_mut() = Some(weak_y);
    
    // When x and y go out of scope, the strong reference count will reach zero,
    // allowing the memory to be correctly deallocated.
}