from django.db import models
from django.conf import settings  # To associate the game with a user
import random

class GuessNumberGame(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    target_number = models.IntegerField()  # The number to guess
    max_attempts = models.IntegerField(default=10)  # Maximum attempts allowed
    current_attempts = models.IntegerField(default=0)  # Attempts so far
    number_range = models.IntegerField(default=50)  # Range of the random number (1 to this number)
    guessed_correctly = models.BooleanField(default=False)  # Whether the number has been guessed
    reward_given = models.BooleanField(default=False)  # nou câmp

    def check_guess(self, guess):
        """Return whether the guess is correct, greater, or lesser"""
        self.current_attempts += 1
        if guess == self.target_number:
            self.guessed_correctly = True
            return 'correct'
        elif guess < self.target_number:
            return 'greater'
        else:
            return 'lesser'

    def is_game_over(self):
        """Return True if the game is over, either because of guesses or winning"""
        return self.guessed_correctly or self.current_attempts >= self.max_attempts
