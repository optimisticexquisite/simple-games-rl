from flask import Flask, request, jsonify, render_template, redirect, url_for
import uuid, random, json, os

app = Flask(__name__)
games = {}  # store game state by gameID

Q_TABLE_FILE = "q_table.json"

def load_q_table():
    if os.path.exists(Q_TABLE_FILE):
        with open(Q_TABLE_FILE, "r") as f:
            return json.load(f)
    else:
        return {"W": {}, "B": {}}

def save_q_table():
    with open(Q_TABLE_FILE, "w") as f:
        json.dump(q_table, f)

# Load the Q-table at startup.
q_table = load_q_table()

def initial_board():
    board = {}
    files = ['a', 'b', 'c', 'd']
    # White pawns at rank 1; Black pawns at rank 4.
    for pos in [f + '1' for f in files]:
        board[pos] = 'W'
    for pos in [f + '4' for f in files]:
        board[pos] = 'B'
    return board

def get_possible_moves(board, player):
    moves = []
    files = ['a', 'b', 'c', 'd']
    for pos, p in board.items():
        if player == 'W' and p == 'W':
            file, rank = pos[0], int(pos[1])
            # White moves upward (increasing rank).
            forward = rank + 1
            if forward <= 4:
                new_pos = file + str(forward)
                if new_pos not in board:
                    moves.append((pos, new_pos))
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
            # Black moves downward (decreasing rank).
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
    items = sorted(board.items())  # sort by cell name
    state_repr = ",".join([f"{pos}:{piece}" for pos, piece in items])
    return player + "|" + state_repr

def choose_action(player, board, game_history):
    possible_moves = get_possible_moves(board, player)
    if not possible_moves:
        return None  # no moves available
    state_key = board_to_state_key(board, player)
    # Initialize Q values for all possible moves in this state if not present.
    if state_key not in q_table[player]:
        q_table[player][state_key] = {}
        for move in possible_moves:
            action_str = move[0] + move[1]
            q_table[player][state_key][action_str] = 20
    # In case new moves have become available that are not yet in the table.
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
    # Record this state-action pair in the game's history.
    game_history.append((player, state_key, chosen_action_str))
    return chosen_move

def check_game_over(board, current_player):
    """
    Game is over if:
      - A pawn reaches the opponent's rank (for white: rank 4, for black: rank 1)
      - The current player has no moves
    """
    for pos, p in board.items():
        rank = int(pos[1])
        if p == 'W' and rank == 4:
            return True, "W"
        if p == 'B' and rank == 1:
            return True, "B"
    if not get_possible_moves(board, current_player):
        # Current player cannot move, so they lose.
        winner = "B" if current_player == "W" else "W"
        return True, winner
    return False, None

def update_q_values(game_history, winner):
    for (player, state_key, action_str) in game_history:
        if state_key in q_table[player] and action_str in q_table[player][state_key]:
            if player == winner:
                q_table[player][state_key][action_str] += 1
            else:
                q_table[player][state_key][action_str] -= 1
    save_q_table()  # Persist Q-table after updating

@app.route('/start', methods=['POST'])
def start():
    data = request.get_json()
    gameID = data.get("gameID", str(uuid.uuid4()))
    board = initial_board()
    # Set up the game state with white's turn and an empty history.
    games[gameID] = {"board": board, "turn": "W", "history": []}
    current_player = "W"
    move = choose_action(current_player, board, games[gameID]["history"])
    if move is None:
        # No moves available—white loses immediately.
        update_q_values(games[gameID]["history"], "B")
        response = {
            "message": "Game Over",
            "winner": "black",
            "gameID": gameID,
            "player": "white",
            "from": None,
            "to": None,
            "qvalues": {"actions": [], "values": []}
        }
        return jsonify(response)
    src, dst = move
    # Execute white's move.
    if dst in board:
        del board[dst]
    board[dst] = "W"
    del board[src]
    # Check if game is over after white's move.
    over, winner = check_game_over(board, "B")
    if over:
        update_q_values(games[gameID]["history"], winner)
        response = {
            "message": "Game Over",
            "winner": "white" if winner=="W" else "black",
            "gameID": gameID,
            "player": "white",
            "from": src,
            "to": dst,
            "qvalues": {"actions": [], "values": []}
        }
        return jsonify(response)
    # Prepare Q values for black's next moves.
    next_player = "B"
    state_key = board_to_state_key(board, next_player)
    next_possible = get_possible_moves(board, next_player)
    if state_key not in q_table[next_player]:
        q_table[next_player][state_key] = {}
        for m in next_possible:
            action_str = m[0] + m[1]
            q_table[next_player][state_key][action_str] = 20
    q_actions = list(q_table[next_player][state_key].keys())
    q_values = [q_table[next_player][state_key][a] for a in q_actions]
    games[gameID]["turn"] = next_player
    response = {
        "player": "white",
        "from": src,
        "to": dst,
        "qvalues": {"actions": q_actions, "values": q_values},
        "gameID": gameID
    }
    return jsonify(response)

@app.route('/continue', methods=['POST'])
def continue_game():
    data = request.get_json()
    gameID = data.get("gameID")
    if gameID not in games:
        return jsonify({"error": "Invalid gameID"})
    board = games[gameID]["board"]
    current_player = games[gameID]["turn"]
    move = choose_action(current_player, board, games[gameID]["history"])
    if move is None:
        # No moves available – current player loses.
        winner = "B" if current_player == "W" else "W"
        update_q_values(games[gameID]["history"], winner)
        response = {
            "message": "Game Over",
            "winner": "white" if winner=="W" else "black",
            "gameID": gameID,
            "player": "white" if current_player=="W" else "black",
            "from": None,
            "to": None,
            "qvalues": {"actions": [], "values": []}
        }
        return jsonify(response)
    src, dst = move
    # Execute the move.
    if dst in board:
        del board[dst]
    board[dst] = current_player
    del board[src]
    # Check if the game is over after this move.
    next_player = "B" if current_player=="W" else "W"
    over, winner = check_game_over(board, next_player)
    if over:
        update_q_values(games[gameID]["history"], winner)
        response = {
            "message": "Game Over",
            "winner": "white" if winner=="W" else "black",
            "gameID": gameID,
            "player": "white" if current_player=="W" else "black",
            "from": src,
            "to": dst,
            "qvalues": {"actions": [], "values": []}
        }
        return jsonify(response)
    # Prepare Q values for the next player's moves.
    state_key = board_to_state_key(board, next_player)
    next_possible = get_possible_moves(board, next_player)
    if state_key not in q_table[next_player]:
        q_table[next_player][state_key] = {}
        for m in next_possible:
            action_str = m[0] + m[1]
            q_table[next_player][state_key][action_str] = 20
    q_actions = list(q_table[next_player][state_key].keys())
    q_values = [q_table[next_player][state_key][a] for a in q_actions]
    games[gameID]["turn"] = next_player
    response = {
        "player": "white" if current_player=="W" else "black",
        "from": src,
        "to": dst,
        "qvalues": {"actions": q_actions, "values": q_values},
        "gameID": gameID
    }
    return jsonify(response)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/play_drag/start', methods=['POST'])
def play_drag_start():
    data = request.get_json()
    player_side = data.get("player_side", "W")  # "W" or "B"
    gameID = str(uuid.uuid4())
    board = initial_board()
    # Set up the game: if the user chooses White, human goes first;
    # if Black, computer makes the first move.
    history = []
    if player_side == "W":
        turn = "W"
        message = "Game started. Your move."
    else:
        # If playing as Black, computer plays as White first.
        comp_move = choose_action("W", board, history)
        if comp_move:
            src, dst = comp_move
            if dst in board:
                del board[dst]
            board[dst] = "W"
            del board[src]
            history.append(("W", board_to_state_key(board, "W"), src+dst))
            turn = "B"
            message = f"Computer played {src+dst}. Your move as Black."
        else:
            turn = "B"
            message = "Game Over"
    games[gameID] = {"board": board, "turn": turn, "history": history, "mode": "play_drag", "player_side": player_side}
    return jsonify({
         "gameID": gameID,
         "board": board,
         "turn": turn,
         "message": message
    })

@app.route('/play_drag/move', methods=['POST'])
def play_drag_move():
    data = request.get_json()
    gameID = data.get("gameID")
    human_from = data.get("from")
    human_to = data.get("to")
    if gameID not in games:
        return jsonify({"error": "Invalid gameID"})
    game = games[gameID]
    board = game["board"]
    player_side = game.get("player_side", "W")
    # Determine human and computer sides.
    human_player = player_side
    computer_player = "B" if player_side == "W" else "W"
    if game["turn"] != human_player:
        return jsonify({"error": "Not your turn."})
    valid_moves = get_possible_moves(board, human_player)
    if (human_from, human_to) not in valid_moves:
        return jsonify({"error": "Invalid move", "valid_moves": [m[0]+m[1] for m in valid_moves]})
    if human_to in board:
        del board[human_to]
    board[human_to] = human_player
    del board[human_from]
    game["history"].append((human_player, board_to_state_key(board, human_player), human_from+human_to))
    over, winner = check_game_over(board, computer_player)
    if over:
        update_q_values(game["history"], winner)
        return jsonify({
              "message": "Game Over",
              "winner": "white" if winner=="W" else "black",
              "board": board,
              "human_move": human_from+human_to,
              "computer_move": None,
              "turn": None
        })
    # Computer's turn.
    comp_move = choose_action(computer_player, board, game["history"])
    if comp_move is None:
        winner = human_player
        update_q_values(game["history"], winner)
        return jsonify({
              "message": "Game Over",
              "winner": "white" if winner=="W" else "black",
              "board": board,
              "human_move": human_from+human_to,
              "computer_move": None,
              "turn": None
        })
    comp_from, comp_to = comp_move
    if comp_to in board:
        del board[comp_to]
    board[comp_to] = computer_player
    del board[comp_from]
    game["history"].append((computer_player, board_to_state_key(board, computer_player), comp_from+comp_to))
    over, winner = check_game_over(board, human_player)
    if over:
        update_q_values(game["history"], winner)
        message = "Game Over"
        turn = None
    else:
        message = "Your move."
        game["turn"] = human_player
        turn = human_player
    valid_moves = get_possible_moves(board, human_player)
    return jsonify({
         "message": message,
         "board": board,
         "human_move": human_from+human_to,
         "computer_move": comp_from+comp_to,
         "possible_moves": [m[0]+m[1] for m in valid_moves],
         "turn": turn,
         "winner": "white" if over and winner=="W" else "black" if over else None
    })

@app.route('/play')
def play_drag():
    return render_template('play.html')

if __name__ == '__main__':
    app.run(debug=True)
