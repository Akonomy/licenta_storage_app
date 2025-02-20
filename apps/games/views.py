from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import GuessNumberGame
from apps.accounts.models import CustomUser
import random
from django.contrib.messages import get_messages

@login_required
def start_game(request):
    if request.method == 'POST':
        # Clear any existing messages
        storage = get_messages(request)
        list(storage)  # Consume all messages

        # Generate a random number range between 50 and 10,000
        number_range = random.randint(50, 5000)

        # Initial attempts is randomly 3 or 4 for the base range of 50
        initial_attempts = random.choice([4, 6])

        # Calculate the number of 150 intervals beyond the base range
        intervals = (number_range - 25) // 100

        # For each interval, randomly decide whether to add an extra attempt
        extra_attempts = sum(random.choice([0, 1]) for _ in range(intervals))

        # Total maximum attempts
        max_attempts = initial_attempts + extra_attempts

        # Randomly select the target number within the range
        target_number = random.randint(1, number_range)

        # Create a new game instance
        game = GuessNumberGame.objects.create(
            user=request.user,
            target_number=target_number,
            number_range=number_range,
            max_attempts=max_attempts
        )
        return redirect('games:game_detail', game_id=game.id)

    return render(request, 'games/start_game.html')

@login_required
def game_detail(request, game_id):
    game = get_object_or_404(GuessNumberGame, id=game_id, user=request.user)
    last_guess = None  # Initialize last_guess

    if request.method == 'POST':
        guess = int(request.POST.get('guess'))
        last_guess = guess  # Store the last guess
        result = game.check_guess(guess)
        game.save()

        if result == 'correct':
            messages.success(request, 'Congratulations! You guessed the correct number.')
        elif result == 'greater':
            messages.info(request, 'The number is greater than your guess.')
        else:
            messages.info(request, 'The number is less than your guess.')

        if game.is_game_over():
            if game.guessed_correctly:
                return redirect('games:game_won', game_id=game.id)  # Redirect to the win page
            else:
                messages.error(request, 'You lost the game. Maximum attempts reached.')
                return redirect('games:game_over', game_id=game.id)

    # Calculate remaining attempts
    remaining_attempts = game.max_attempts - game.current_attempts

    return render(request, 'games/game_detail.html', {
        'game': game,
        'remaining_attempts': remaining_attempts,
        'last_guess': last_guess,
    })


@login_required
def game_won(request, game_id):
    game = get_object_or_404(GuessNumberGame, id=game_id, user=request.user)
    
    # Dacă recompensa a fost deja acordată, nu o mai acorda din nou
    if game.reward_given:
        messages.info(request, "Recompensa a fost deja acordată.")
        return render(request, 'games/game_won.html', {})

    # Base reward
    base_coins = 15
    
    # Bonus pentru încercări rămase
    remaining_attempts = game.max_attempts - game.current_attempts
    remaining_attempts_bonus = remaining_attempts * random.randint(1, 5)
    
    # Bonus de dificultate
    difficulty_bonus = round(game.number_range / game.max_attempts / 10)
    
    # Total monede
    total_coins = base_coins + remaining_attempts_bonus + difficulty_bonus
    
    # Actualizează monedele utilizatorului
    user = request.user
    user.coins += total_coins
    user.save()

    # Marchează jocul ca având recompensa acordată
    game.reward_given = True
    game.save()

    return render(request, 'games/game_won.html', {
        'base_coins': base_coins,
        'remaining_attempts_bonus': remaining_attempts_bonus,
        'difficulty_bonus': difficulty_bonus,
        'total_coins': total_coins
    })

@login_required
def game_over(request, game_id):
    game = get_object_or_404(GuessNumberGame, id=game_id, user=request.user)
    return render(request, 'games/game_over.html', {'game': game})
