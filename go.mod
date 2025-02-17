module robin

go 1.23.2

replace robin/nucleotide => ./nucleotide

replace robin/strand => ./strand

require robin/strand v0.0.0-00010101000000-000000000000

require robin/nucleotide v0.0.0-00010101000000-000000000000 // indirect
