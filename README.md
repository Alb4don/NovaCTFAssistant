### `Overview`

- It connects to a local Ollama instance to provide dynamic analysis for challenges on platforms like TryHackMe and Hack The Box.
  
- When Nova cannot reach ***http://localhost:11434***, it routes your query to the OfflineAnalysisEngine.

- This engine uses compiled regex patterns to identify the CTF category mapping terms like blind sql or steghide to one of 25 specific categories ***(SQLi, XSS, Pwn, Stego, Crypto, PrivEsc, etc.)***.

- It retrieves a pre-written block of verified techniques, exact command syntax, and relevant tool names for that category. It will not invent a command because it only outputs what is hardcoded in its dictionary.

<img width="1056" height="690" alt="novafrontend" src="https://github.com/user-attachments/assets/0aef3aaf-a57b-4cf3-883c-471024a38a6a" />

<img width="670" height="572" alt="front2" src="https://github.com/user-attachments/assets/fadf7d72-aaf1-49bb-946b-c894a4172f39" />

### `Setup`

- Nova is built entirely on the Python standard library (tkinter, sqlite3, urllib, hashlib).
  
- Start Ollama and pull a model:

        ollama pull llama3.2:1b
        ollama serve

- Run the application:

        python nova.py


### `AI model architecture`

###### Episodic Semantic Memory

- This tool was designed so as not to rely solely on the LLM's context window to remember your session.

- Every query you send is hashed using SHA-512 to create a deterministic 64-dimensional vector embedding. This vector and the text are stored in the local SQLite database.

- Before sending a new query to the LLM, Nova calculates the cosine similarity between the new query and the last 500 stored interactions.

- If a past episode exceeds a 0.3 similarity threshold, Nova injects the text of that past interaction directly into the system prompt.

- This allows the assistant to recall specific nuances from earlier in your session without passing the entire chat history to the model.

###### UCB1 Prompt Selection

- The tool maintains a set of system prompts. It starts with five distinct prompts.

- It selects which prompt to use via the ***Upper Confidence Bound 1 (UCB1) algorithm***, treating prompt selection as a multi armed bandit problem.

- The math balances exploiting prompts that historically yield high user reward scores with exploring less used prompts.

-  Every response includes Helpful and Not helpful buttons. Clicking them applies a +1.0 or -0.5 reward to that specific prompt's running score and updates the stored episodic memory entry.

###### Automatic Prompt Engineering (APE)

- Every 10 analyses, Nova evaluates the set of prompts. It discards the worst-performing prompt ***(lowest UCB1 score)*** and generates a replacement.

- If Ollama is running, a new prompt is derived by truncating the best-performing prompt and appending a mutation phrase.

- If Ollama is offline, this evolution still occurs using a basic local string manipulation, though the resulting variants are less creative than LLM generated ones.

### `HTML Report Export`

- Clicking Report in the header writes a standalone Bootstrap 5 HTML file to disk.

- The file contains the raw query, the full response, the validation warnings, any similar past episodes pulled from memory, and the current UCB1 prompt metrics.

### `Notice`

- This tool is under development and is being provided "as is"; it may make errors and has certain limitations. Improvements will be implemented as time permits.

- Feel free to contribute to the project's improvement.
