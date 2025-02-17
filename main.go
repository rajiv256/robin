package main

import (
	"fmt"
	"robin/strand"
)

func main() {
	fmt.Println("Hello!")

	// Test script
	s := strand.NewStrand("ACGT")
	fmt.Println(strand.Length(s))
	//fmt.Println(s)
}
