import sys
import subprocess

def main():
    # Join all arguments as the commit message, defaulting to "quick commit" if none provided
    if len(sys.argv) > 1:
        commit_message = " ".join(sys.argv[1:])
    else:
        commit_message = "quick commit"
        
    try:
        print(f"Staging all changes...")
        subprocess.run(["git", "add", "-A"], check=True)
        
        print(f"Committing with message: '{commit_message}'")
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        
        print(f"Pushing to remote repository...")
        subprocess.run(["git", "push"], check=True)
        
        print("Success: git add, commit, and push completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error during execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
