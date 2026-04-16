#!/usr/bin/env python3
"""
Test script for the decoupled RAG agent.
Allows testing the LangGraph agent independently from the UI.
"""

from pathlib import Path
import sys

# Add src directory to path
sys.path.append(str(Path(__file__).parent / "src"))

from agents.rag_agent import RAGAgent


def test_agent():
    """Test the RAG agent with sample queries."""
    print("🧪 Testing RAG Agent")
    print("=" * 50)

    try:
        # Initialize agent
        print("1. Initializing agent...")
        agent = RAGAgent()
        print("✅ Agent initialized successfully\n")

        # Test queries
        test_queries = [
            "What documents are available?",
            "What is our refund policy for late deliveries?",
            "What allergens are in Margherita Pizza?",
            "Tell me about food-safety temperature controls",
        ]

        for i, query in enumerate(test_queries, 1):
            print(f"{i}. Testing query: '{query}'")
            print("-" * 40)

            result = agent.invoke(query)

            if result["success"]:
                print(f"✅ Response: {result['response'][:200]}...")
                if len(result["response"]) > 200:
                    print("   (truncated)")
            else:
                print(f"❌ Error: {result['response']}")

            print()

        print("🎉 All tests completed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

    return True


def interactive_test():
    """Interactive testing mode."""
    print("🔬 Interactive Agent Testing")
    print("=" * 50)

    try:
        agent = RAGAgent()
        print("✅ Agent ready for interactive testing")
        print("Commands: 'quit' to exit, 'help' for help\n")

        while True:
            try:
                query = input("🔍 Enter your question: ").strip()

                if query.lower() in ["quit", "exit", "q"]:
                    print("👋 Goodbye!")
                    break

                if query.lower() == "help":
                    print("\nTest queries you can try:")
                    print("• What documents are available?")
                    print("• What is our refund policy for late deliveries?")
                    print("• What allergens are in Margherita Pizza?")
                    print("• Show me the food-safety temperature controls")
                    print("• Top-selling dishes in Berlin last month")
                    continue

                if not query:
                    continue

                print("\n🤖 Processing...")
                result = agent.invoke(query)

                print("\n" + "=" * 60)
                if result["success"]:
                    print(f"✅ Response:\n{result['response']}")
                else:
                    print(f"❌ Error: {result['response']}")
                print("=" * 60)

            except KeyboardInterrupt:
                print("\n👋 Exiting...")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")

    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test the RAG agent")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")

    args = parser.parse_args()

    if args.interactive:
        interactive_test()
    else:
        test_agent()
