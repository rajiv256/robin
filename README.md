# robin
A package to create orthogonal strand sequences of DNA/RNA for strand displacement. 

## Getting Started

Install `python3.10`

Create a virtual environment at the content root and activate it.  

> `python3 -m venv venv`

> `source venv/bin/activate`

Set environment variables, for now the `PYTHONPATH`. Make sure you are inside the root folder `**/robin/`.
Verify if it is set correctly to `**/robin`. 

> `export PYTHONPATH=$(pwd)`

> echo $PYTHONPATH 

Install the requirements.

> `pip install -r requirements.txt`

Try to run the source or any other util files with a main function `if __name__=="__main__"` in them. You must run them from the content root. 
For example: 

> `python src/objects.py`

should return ... 
```python
d1 (3) d2 (4) ø-d1 (3)--d2 (4)--> ø-d2* (4)--d1* (3)-->
```
