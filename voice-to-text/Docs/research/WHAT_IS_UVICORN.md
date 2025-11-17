# What is Uvicorn?

## Simple Answer

**Uvicorn is the web server that runs your FastAPI application.**

Think of it like this:
- **FastAPI** = The restaurant (your app logic, routes, endpoints)
- **Uvicorn** = The waiter/server (handles HTTP requests, serves responses)

---

## The Analogy

Imagine a restaurant:

```
Customer (Browser) 
    ↓
    "I want to order food" (HTTP Request)
    ↓
Waiter (Uvicorn)
    ↓
    Takes order to kitchen
    ↓
Kitchen (FastAPI)
    ↓
    Prepares food (processes request, runs your code)
    ↓
Waiter (Uvicorn)
    ↓
    Brings food back (HTTP Response)
    ↓
Customer (Browser)
```

**Uvicorn** is the waiter - it:
- Listens for customers (HTTP requests)
- Takes orders to the kitchen (passes requests to FastAPI)
- Brings food back (sends responses to browser)

**FastAPI** is the kitchen - it:
- Has the recipes (your Python code)
- Prepares the food (processes requests)
- Returns the result (sends data back)

---

## Technical Explanation

### What Uvicorn Does

1. **Listens on a port** (like port 8000)
   - Waits for HTTP requests from browsers/clients

2. **Receives HTTP requests**
   - "GET /" (homepage)
   - "POST /transcribe" (upload audio file)
   - etc.

3. **Passes requests to FastAPI**
   - FastAPI processes the request (runs your Python code)
   - FastAPI returns a response

4. **Sends HTTP responses back**
   - HTML pages
   - JSON data
   - File downloads
   - etc.

### Why You Need It

**FastAPI is just Python code** - it doesn't know how to:
- Listen on network ports
- Handle HTTP protocol
- Manage connections
- Handle multiple requests at once

**Uvicorn handles all of that** - it's a production-ready ASGI server.

---

## What is ASGI?

**ASGI** = Asynchronous Server Gateway Interface

- It's a standard way for Python web frameworks (like FastAPI) to communicate with web servers
- Similar to WSGI (used by Flask, Django), but supports async/await
- Allows handling multiple requests simultaneously (async)

### The Stack

```
Browser
    ↓ HTTP
Uvicorn (ASGI Server)
    ↓ ASGI Protocol
FastAPI (Web Framework)
    ↓
Your Python Code
```

---

## Why Uvicorn Specifically?

Uvicorn is:
- ✅ **Fast** - Built on `uvloop` (fast event loop)
- ✅ **Async** - Handles many requests simultaneously
- ✅ **Standard** - Implements ASGI protocol
- ✅ **Production-ready** - Used in real production systems
- ✅ **Easy** - Simple to configure and run

### Alternatives

You *could* use other ASGI servers:
- **Hypercorn** - Another ASGI server
- **Daphne** - Django's ASGI server
- **Gunicorn + Uvicorn workers** - For production scaling

But **Uvicorn is the standard** for FastAPI development.

---

## How It Works in Your Project

### When you run:
```bash
uvicorn app.main:app --port 8000
```

### Uvicorn:
1. Imports `app.main` (your `app/main.py` file)
2. Finds the `app` object (your FastAPI instance)
3. Starts listening on port 8000
4. When a request comes in:
   - Parses the HTTP request
   - Calls the appropriate FastAPI route
   - Waits for FastAPI to process it
   - Sends the response back

### Example Flow:

```
1. Browser: GET http://localhost:8000/
   ↓
2. Uvicorn: Receives request, parses it
   ↓
3. Uvicorn: Calls FastAPI app
   ↓
4. FastAPI: Runs your @app.get("/") function
   ↓
5. FastAPI: Returns HTMLResponse("<h1>Hello</h1>")
   ↓
6. Uvicorn: Converts to HTTP response
   ↓
7. Browser: Displays the page
```

---

## Key Concepts

### Port
- **Port 8000** = The "door number" where your server listens
- Like an apartment number - requests go to `localhost:8000`
- You can change it: `--port 8080` (use port 8080 instead)

### Host
- **127.0.0.1** = localhost (only accessible from your computer)
- **0.0.0.0** = accessible from network (for production)
- Default: `127.0.0.1` (safe for development)

### Reload
- **--reload** = Auto-restart when code changes
- Great for development (see changes immediately)
- **Don't use in production** (slower, less secure)

---

## In Your Code

When you run `python -m app.main`, look at the bottom of `app/main.py`:

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",  # Where to find FastAPI app
        host="127.0.0.1",  # Listen on localhost
        port=8000,  # Port number
        reload=True  # Auto-reload on changes
    )
```

This is **Option 2** - Python calls uvicorn for you.

**Option 3** is calling uvicorn directly:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Same result, just different way to start it!

---

## Summary

- **Uvicorn** = Web server that runs FastAPI apps
- **FastAPI** = Web framework (your Python code)
- **ASGI** = Protocol they use to communicate
- **Port 8000** = Where it listens for requests
- **--reload** = Auto-restart on code changes (dev only)

**Think of it as:** Uvicorn is the delivery service, FastAPI is the restaurant, and your code is the menu!

