/// Checks how accesses from one subtree affect other subtrees.
/// This test checks that an access from a newer created subtree
/// performs a wildcard access on all earlier trees.
pub fn main() {
    let mut x: u32 = 42;

    let ref_base = &mut x;

    let int0 = ref_base as *mut u32 as usize;
    let wild = int0 as *mut u32;

    // Fix: Use raw pointers instead of &mut to allow aliasing.
    // Raw pointers do not have the same exclusivity requirements as mutable references.
    let reb1 = wild;

    let reb2 = wild;

    // Create a mutable reference from one of the raw pointers only when needed.
    let ref3 = unsafe { &mut *reb2 };
    let _int3 = ref3 as *mut u32 as usize;
    //    ┌──────────────┐
    //    │              │
    //    │ptr_base(Res)*│        *                *
    //    │              │        │                │
    //    └──────────────┘        │                │
    //                            │                │
    //                            │                │
    //                            ▼                ▼
    //                      ┌────────────┐   ┌────────────┐
    //                      │            │   │            │
    //                      │ reb1       ├   │ reb2       ├
    //                      │            │   │            │
    //                      └────────────┘   └──────┬─────┘
    //                                              │
    //                                              │
    //                                              ▼
    //                                       ┌────────────┐
    //                                       │            │
    //                                       │ ref3(Res)* │
    //                                       │            │
    //                                       └────────────┘

    // This access no longer disables reb1 because reb1 is a raw pointer,
    // which does not carry the unique-access guarantees of &mut.
    *ref3 = 13;

    // Accessing the raw pointer reb1 is now safe.
    let _val = unsafe { *reb1 };
}