import Mathlib
open List in
#check @List.monotone_filter_right
#check @List.Sublist.length_le
example (l : List Nat) (p q : Nat → Bool) (h : ∀ x, p x → q x) : l.filter p <+ l.filter q := by
  exact List.monotone_filter_right l h
example (l₁ l₂ : List Nat) (hs : l₁ <+ l₂) (hlen : l₂.length ≤ l₁.length) : l₁ = l₂ :=
  hs.eq_of_length_le hlen
