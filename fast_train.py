import uuid, random, json, os, time

Q_TABLE_FILE = "q_table.json"

def load_q_table():
    if os.path.exists(Q_TABLE_FILE):
        with open(Q_TABLE_FILE, "r") as f:
            return json.load(f)
    else:
        return {"W": {}, "B": {}}

def save_q_table(q_table):
    with open(Q_TABLE_FILE, "w") as f:
        json.dump(q_table, f)

# Load (or initialize) the global Q-table.
q_table = load_q_table()

def initial_board():
    board = {}
    # White pawns at rank 1; Black pawns at rank 3.
    for pos in ['a1', 'b1', 'c1']:
        board[pos] = 'W'
    for pos in ['a3', 'b3', 'c3']:
        board[pos] = 'B'
    return board

def get_possible_moves(board, player):
    moves = []
    files = ['a', 'b', 'c']
    for pos, p in board.items():
        if player == 'W' and p == 'W':
            file, rank = pos[0], int(pos[1])
            # Forward move:
            forward = rank + 1
            if forward <= 3:
                new_pos = file + str(forward)
                if new_pos not in board:
                    moves.append((pos, new_pos))
            # Diagonal captures:
            file_index = files.index(file)
            for diff in [-1, 1]:
                new_file_index = file_index + diff
                if 0 <= new_file_index < len(files):
                    new_file = files[new_file_index]
                    diag_pos = new_file + str(rank + 1)
                    if diag_pos in board and board[diag_pos] == 'B':
                        moves.append((pos, diag_pos))
        elif player == 'B' and p == 'B':
            file, rank = pos[0], int(pos[1])
            forward = rank - 1
            if forward >= 1:
                new_pos = file + str(forward)
                if new_pos not in board:
                    moves.append((pos, new_pos))
            file_index = files.index(file)
            for diff in [-1, 1]:
                new_file_index = file_index + diff
                if 0 <= new_file_index < len(files):
                    new_file = files[new_file_index]
                    diag_pos = new_file + str(rank - 1)
                    if diag_pos in board and board[diag_pos] == 'W':
                        moves.append((pos, diag_pos))
    return moves

def board_to_state_key(board, player):
    """Return a canonical string representation of the board along with the player."""
    items = sorted(board.items())  # sort by cell name
    state_repr = ",".join([f"{pos}:{piece}" for pos, piece in items])
    return player + "|" + state_repr

def choose_action(player, board, game_history):
    """
    Choose an action for the player based on the Q values for the current state.
    Record the state-action pair in game_history.
    """
    possible_moves = get_possible_moves(board, player)
    if not possible_moves:
        return None
    state_key = board_to_state_key(board, player)
    # Initialize if state not seen before.
    if state_key not in q_table[player]:
        q_table[player][state_key] = {}
        for move in possible_moves:
            action_str = move[0] + move[1]
            q_table[player][state_key][action_str] = 20
    # Also add any new moves.
    for move in possible_moves:
        action_str = move[0] + move[1]
        if action_str not in q_table[player][state_key]:
            q_table[player][state_key][action_str] = 20

    actions = list(q_table[player][state_key].keys())
    q_values = [q_table[player][state_key][a] for a in actions]
    total = sum(q_values)
    probabilities = [q / total for q in q_values] if total > 0 else [1/len(q_values)] * len(q_values)
    chosen_action_str = random.choices(actions, weights=probabilities, k=1)[0]
    chosen_move = None
    for move in possible_moves:
        if move[0] + move[1] == chosen_action_str:
            chosen_move = move
            break
    # Record the state-action.
    game_history.append((player, state_key, chosen_action_str))
    return chosen_move

def check_game_over(board, next_player):
    """
    Game is over if:
      - A pawn reaches the opponent's rank (for white: rank 3, for black: rank 1)
      - The next player has no moves.
    Returns (True, winner) or (False, None).
    """
    for pos, p in board.items():
        rank = int(pos[1])
        if p == 'W' and rank == 3:
            return True, "W"
        if p == 'B' and rank == 1:
            return True, "B"
    if not get_possible_moves(board, next_player):
        winner = "B" if next_player == "W" else "W"
        return True, winner
    return False, None

def update_q_values(game_history, winner):
    """Update Q values for every recorded state-action pair."""
    for (player, state_key, action_str) in game_history:
        if state_key in q_table[player] and action_str in q_table[player][state_key]:
            if player == winner:
                q_table[player][state_key][action_str] += 1
            else:
                q_table[player][state_key][action_str] -= 1
    # Persist the Q table.
    save_q_table(q_table)

def simulate_game():
    """Simulate a single game and update Q values at the end. Return the winner and number of moves."""
    board = initial_board()
    game_history = []
    current_player = "W"  # White always starts.
    while True:
        move = choose_action(current_player, board, game_history)
        if move is None:
            # No moves available: current player loses.
            winner = "B" if current_player == "W" else "W"
            break
        src, dst = move
        # Execute move: remove captured piece if any.
        if dst in board:
            del board[dst]
        board[dst] = current_player
        del board[src]
        # Check if game is over.
        next_player = "B" if current_player == "W" else "W"
        over, winner = check_game_over(board, next_player)
        if over:
            break
        current_player = next_player
    update_q_values(game_history, winner)
    return winner, len(game_history)

if __name__ == '__main__':
    NUM_GAMES = 10000
    wins = {"W": 0, "B": 0}
    total_moves = 0
    start_time = time.time()
    for i in range(NUM_GAMES):
        winner, num_moves = simulate_game()
        wins[winner] += 1
        total_moves += num_moves
        if (i+1) % 100 == 0:
            print(f"Game {i+1}: Winner = {winner}, Moves = {num_moves}")
    end_time = time.time()
    print("\nTraining complete!")
    print(f"Total games: {NUM_GAMES}")
    print(f"White wins: {wins['W']}, Black wins: {wins['B']}")
    print(f"Average moves per game: {total_moves / NUM_GAMES:.2f}")
    print(f"Total training time: {end_time - start_time:.2f} seconds")
