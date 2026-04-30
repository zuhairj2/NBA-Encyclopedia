from agent.agent import run_agent

if __name__ == "__main__":
    print("Basketball Analyst")
    while True:
        user_input = input("Ask a question (or 'quit'): ")
        if user_input.lower() == "quit":
            break
        response = run_agent(user_input)
        print("\n", response, "\n")