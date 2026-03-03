#![feature(explicit_tail_calls)]
#![allow(incomplete_features)]

fn main() {
    become f();
}

fn f() {}