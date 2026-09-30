(function () {
  'use strict';

  var COLS = 10;
  var ROWS = 20;
  var BLOCK = 30;

  var canvas = document.getElementById('board');
  var ctx = canvas.getContext('2d');
  var scoreEl = document.getElementById('score');
  var levelEl = document.getElementById('level');
  var linesEl = document.getElementById('lines');
  var overlayEl = document.getElementById('game-over-overlay');
  var finalScoreEl = document.getElementById('final-score');
  var restartBtn = document.getElementById('restart-btn');
  var pausedOverlayEl = document.getElementById('paused-overlay');

  var SHAPES = {
    I: {
      color: '#00e5e5',
      rotations: [
        [[0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]],
        [[0, 0, 1, 0], [0, 0, 1, 0], [0, 0, 1, 0], [0, 0, 1, 0]],
        [[0, 0, 0, 0], [0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0]],
        [[0, 1, 0, 0], [0, 1, 0, 0], [0, 1, 0, 0], [0, 1, 0, 0]]
      ]
    },
    O: {
      color: '#e5e500',
      rotations: [
        [[1, 1], [1, 1]],
        [[1, 1], [1, 1]],
        [[1, 1], [1, 1]],
        [[1, 1], [1, 1]]
      ]
    },
    T: {
      color: '#a000e0',
      rotations: [
        [[0, 1, 0], [1, 1, 1], [0, 0, 0]],
        [[0, 1, 0], [0, 1, 1], [0, 1, 0]],
        [[0, 0, 0], [1, 1, 1], [0, 1, 0]],
        [[0, 1, 0], [1, 1, 0], [0, 1, 0]]
      ]
    },
    S: {
      color: '#00e000',
      rotations: [
        [[0, 1, 1], [1, 1, 0], [0, 0, 0]],
        [[0, 1, 0], [0, 1, 1], [0, 0, 1]],
        [[0, 0, 0], [0, 1, 1], [1, 1, 0]],
        [[1, 0, 0], [1, 1, 0], [0, 1, 0]]
      ]
    },
    Z: {
      color: '#e00000',
      rotations: [
        [[1, 1, 0], [0, 1, 1], [0, 0, 0]],
        [[0, 0, 1], [0, 1, 1], [0, 1, 0]],
        [[0, 0, 0], [1, 1, 0], [0, 1, 1]],
        [[0, 1, 0], [1, 1, 0], [1, 0, 0]]
      ]
    },
    J: {
      color: '#2020e5',
      rotations: [
        [[1, 0, 0], [1, 1, 1], [0, 0, 0]],
        [[0, 1, 1], [0, 1, 0], [0, 1, 0]],
        [[0, 0, 0], [1, 1, 1], [0, 0, 1]],
        [[0, 1, 0], [0, 1, 0], [1, 1, 0]]
      ]
    },
    L: {
      color: '#e07000',
      rotations: [
        [[0, 0, 1], [1, 1, 1], [0, 0, 0]],
        [[0, 1, 0], [0, 1, 0], [0, 1, 1]],
        [[0, 0, 0], [1, 1, 1], [1, 0, 0]],
        [[1, 1, 0], [0, 1, 0], [0, 1, 0]]
      ]
    }
  };

  var PIECE_TYPES = ['I', 'O', 'T', 'S', 'Z', 'J', 'L'];

  var LINE_SCORES = [0, 100, 300, 500, 800];
  var LINES_PER_LEVEL = 10;
  var BASE_DROP_INTERVAL = 1000;
  var MIN_DROP_INTERVAL = 100;
  var DROP_STEP = 75;

  // Keys the game intercepts; default browser behavior (page scroll, button
  // activation) must be suppressed for these regardless of run state so the
  // game-over overlay never lets Space/Arrow keys scroll the page.
  var CONTROLLED_KEYS = ['ArrowLeft', 'ArrowRight', 'ArrowDown', 'ArrowUp', ' ', 'Spacebar'];

  var board = createBoard();
  var bag = [];
  var current = null;
  var score = 0;
  var lines = 0;
  var level = 0;
  var dropInterval = BASE_DROP_INTERVAL;
  var dropCounter = 0;
  var lastTime = null;
  var gameRunning = false;
  var paused = false;
  var rafId = null;
  // Explicit latch so a hard drop can only fire once per physical
  // press-release cycle of Space, independent of e.repeat behavior.
  var spaceHeld = false;

  function createBoard() {
    var grid = [];
    for (var r = 0; r < ROWS; r++) {
      grid.push(new Array(COLS).fill(0));
    }
    return grid;
  }

  function refillBag() {
    var pool = PIECE_TYPES.slice();
    for (var i = pool.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = pool[i];
      pool[i] = pool[j];
      pool[j] = tmp;
    }
    bag = bag.concat(pool);
  }

  function nextType() {
    if (bag.length === 0) refillBag();
    return bag.shift();
  }

  function spawnPiece() {
    var type = nextType();
    var shape = SHAPES[type];
    var size = shape.rotations[0].length;
    var col = Math.floor((COLS - size) / 2);
    var piece = {
      type: type,
      rotation: 0,
      row: 0,
      col: col,
      color: shape.color
    };
    current = piece;
    if (collides(matrixOf(piece), piece.row, piece.col)) {
      triggerGameOver();
    }
  }

  function matrixOf(piece) {
    return SHAPES[piece.type].rotations[piece.rotation];
  }

  function collides(matrix, row, col) {
    for (var r = 0; r < matrix.length; r++) {
      for (var c = 0; c < matrix[r].length; c++) {
        if (!matrix[r][c]) continue;
        var boardRow = row + r;
        var boardCol = col + c;
        if (boardCol < 0 || boardCol >= COLS || boardRow >= ROWS) return true;
        if (boardRow < 0) continue;
        if (board[boardRow][boardCol]) return true;
      }
    }
    return false;
  }

  function tryMove(dRow, dCol) {
    if (!current) return false;
    var newRow = current.row + dRow;
    var newCol = current.col + dCol;
    var matrix = matrixOf(current);
    if (collides(matrix, newRow, newCol)) return false;
    current.row = newRow;
    current.col = newCol;
    return true;
  }

  // Minimal wall kick: try the naive position, then a single-cell nudge
  // left/right, before giving up. Deliberately not a full SRS per-piece
  // kick table -- just enough for rotations blocked only by an adjacent
  // wall/block to still succeed, matching the spec's "no valid kick
  // position" rejection language without the complexity of true SRS.
  var ROTATION_KICKS = [[0, 0], [0, -1], [0, 1]];

  function tryRotate() {
    if (!current) return;
    var shape = SHAPES[current.type];
    var newRotation = (current.rotation + 1) % shape.rotations.length;
    var matrix = shape.rotations[newRotation];
    for (var i = 0; i < ROTATION_KICKS.length; i++) {
      var dCol = ROTATION_KICKS[i][1];
      if (!collides(matrix, current.row, current.col + dCol)) {
        current.rotation = newRotation;
        current.col += dCol;
        return;
      }
    }
  }

  function hardDrop() {
    if (!current) return;
    while (tryMove(1, 0)) {}
    lockPiece();
  }

  function lockPiece() {
    var matrix = matrixOf(current);
    for (var r = 0; r < matrix.length; r++) {
      for (var c = 0; c < matrix[r].length; c++) {
        if (!matrix[r][c]) continue;
        var boardRow = current.row + r;
        var boardCol = current.col + c;
        if (boardRow >= 0 && boardRow < ROWS && boardCol >= 0 && boardCol < COLS) {
          board[boardRow][boardCol] = current.color;
        }
      }
    }
    clearLines();
    spawnPiece();
  }

  function clearLines() {
    var cleared = 0;
    for (var r = ROWS - 1; r >= 0; r--) {
      if (board[r].every(function (cell) { return cell !== 0; })) {
        board.splice(r, 1);
        board.unshift(new Array(COLS).fill(0));
        cleared++;
        r++;
      }
    }
    if (cleared > 0) {
      score += LINE_SCORES[cleared] * (level + 1);
      lines += cleared;
      updateLevel();
      updateHud();
    }
  }

  function updateLevel() {
    var newLevel = Math.floor(lines / LINES_PER_LEVEL);
    if (newLevel > level) {
      level = newLevel;
      var newInterval = BASE_DROP_INTERVAL - level * DROP_STEP;
      dropInterval = Math.max(MIN_DROP_INTERVAL, newInterval);
    }
  }

  function updateHud() {
    scoreEl.textContent = score;
    levelEl.textContent = level;
    linesEl.textContent = lines;
  }

  function triggerGameOver() {
    gameRunning = false;
    paused = false;
    finalScoreEl.textContent = score;
    overlayEl.classList.remove('hidden');
  }

  function stopLoop() {
    if (rafId !== null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
  }

  function resetGame() {
    stopLoop();
    board = createBoard();
    bag = [];
    score = 0;
    lines = 0;
    level = 0;
    dropInterval = BASE_DROP_INTERVAL;
    dropCounter = 0;
    lastTime = null;
    paused = false;
    overlayEl.classList.add('hidden');
    updateHud();
    spawnPiece();
    gameRunning = true;
    rafId = requestAnimationFrame(loop);
  }

  function drawCell(x, y, color) {
    ctx.fillStyle = color;
    ctx.fillRect(x * BLOCK, y * BLOCK, BLOCK, BLOCK);
    ctx.strokeStyle = 'rgba(0,0,0,0.35)';
    ctx.lineWidth = 1;
    ctx.strokeRect(x * BLOCK + 0.5, y * BLOCK + 0.5, BLOCK - 1, BLOCK - 1);
  }

  function draw() {
    ctx.fillStyle = '#0a0a12';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    for (var r = 0; r < ROWS; r++) {
      for (var c = 0; c < COLS; c++) {
        if (board[r][c]) drawCell(c, r, board[r][c]);
      }
    }

    if (current) {
      var matrix = matrixOf(current);
      for (var mr = 0; mr < matrix.length; mr++) {
        for (var mc = 0; mc < matrix[mr].length; mc++) {
          if (!matrix[mr][mc]) continue;
          var boardRow = current.row + mr;
          var boardCol = current.col + mc;
          if (boardRow >= 0) drawCell(boardCol, boardRow, current.color);
        }
      }
    }
  }

  function loop(timestamp) {
    if (!gameRunning) {
      rafId = null;
      return;
    }
    rafId = requestAnimationFrame(loop);

    if (paused) {
      // Discard elapsed time while paused so a stale delta never lands
      // once focus returns.
      lastTime = null;
      return;
    }

    if (lastTime === null) lastTime = timestamp;
    var delta = timestamp - lastTime;
    lastTime = timestamp;
    dropCounter += delta;
    if (dropCounter > dropInterval) {
      if (!tryMove(1, 0)) lockPiece();
      dropCounter = 0;
    }
    draw();
  }

  function pause() {
    if (!gameRunning) return;
    paused = true;
    pausedOverlayEl.classList.remove('hidden');
  }

  function resume() {
    if (!gameRunning) return;
    paused = false;
    dropCounter = 0;
    lastTime = null;
    pausedOverlayEl.classList.add('hidden');
  }

  function handleVisibilityChange() {
    if (document.hidden) {
      pause();
    } else {
      resume();
    }
  }

  function handleKeydown(e) {
    if (CONTROLLED_KEYS.indexOf(e.key) === -1) return;
    // Always suppress default scroll/activation for controlled keys, even
    // when the game isn't actively running (e.g. game-over overlay).
    e.preventDefault();
    if (!gameRunning || paused) return;
    switch (e.key) {
      case 'ArrowLeft':
        tryMove(0, -1);
        break;
      case 'ArrowRight':
        tryMove(0, 1);
        break;
      case 'ArrowDown':
        if (!tryMove(1, 0)) lockPiece();
        dropCounter = 0;
        break;
      case 'ArrowUp':
        // OS key auto-repeat must not spam rotation.
        if (e.repeat) break;
        tryRotate();
        break;
      case ' ':
      case 'Spacebar':
        // OS key auto-repeat must not spam hard drop; spaceHeld is a
        // second, explicit latch independent of e.repeat semantics.
        if (e.repeat) break;
        if (!spaceHeld) {
          spaceHeld = true;
          hardDrop();
          dropCounter = 0;
        }
        break;
      default:
        break;
    }
  }

  function handleKeyup(e) {
    if (e.key === ' ' || e.key === 'Spacebar') {
      spaceHeld = false;
    }
  }

  document.addEventListener('keydown', handleKeydown);
  document.addEventListener('keyup', handleKeyup);
  document.addEventListener('visibilitychange', handleVisibilityChange);
  window.addEventListener('blur', pause);
  window.addEventListener('focus', resume);

  restartBtn.addEventListener('click', function () {
    resetGame();
    // Drop keyboard focus so a lingering Space keyup doesn't re-trigger
    // this button's synthetic click while the new game is in progress.
    restartBtn.blur();
  });

  updateHud();
  spawnPiece();
  gameRunning = true;
  rafId = requestAnimationFrame(loop);
})();
