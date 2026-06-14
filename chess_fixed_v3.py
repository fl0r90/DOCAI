from flask import Flask, request, jsonify, render_template_string
import chess
import random

app = Flask(__name__)
board = chess.Board()

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Chess Master Qwen</title>
    <link rel="stylesheet" href="https://unpkg.com/@chrisoakman/chessboardjs@1.0.0/dist/chessboard-1.0.0.min.css">
    <script src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <script src="https://unpkg.com/@chrisoakman/chessboardjs@1.0.0/dist/chessboard-1.0.0.min.js"></script>
    <style>#board { width: 400px; margin: 50px auto; }</style>
</head>
<body style="background: #222; color: white; text-align: center;">
    <h1>Chess Master (Qwen AI)</h1>
    <div id="board"></div>
    <p id="status">Trage o piesa pentru a incepe!</p>
    <script>
        var board = Chessboard('board', {
            draggable: true,
            position: 'start',
            pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
            onDrop: function(source, target) {
                if (source === target) return;
                var move = source + target;
                $.ajax({
                    url: '/move',
                    type: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({move: move}),
                    success: function(data) {
                        board.position(data.fen);
                        $('#status').text('AI a mutat: ' + data.ai_move);
                    },
                    error: function() {
                        $('#status').text('Mutare invalida!');
                        return 'snapback';
                    }
                });
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/move', methods=['POST'])
def make_move():
    data = request.json
    move_uci = data.get('move')
    try:
        move = chess.Move.from_uci(move_uci)
        if move in board.legal_moves:
            board.push(move)
            if not board.is_game_over():
                legal_moves = list(board.legal_moves)
                ai_move = random.choice(legal_moves)
                board.push(ai_move)
                return jsonify({'fen': board.fen(), 'ai_move': ai_move.uci()})
            return jsonify({'fen': board.fen(), 'ai_move': 'Game Over'})
    except:
        pass
    return jsonify({'error': 'Invalid'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005)
