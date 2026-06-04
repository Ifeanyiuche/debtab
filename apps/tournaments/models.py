from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class Tournament(models.Model):
    FORMAT_BP = 'BP'
    FORMAT_WSDC = 'WSDC'
    FORMAT_PS = 'PS'
    FORMAT_CHOICES = [
        (FORMAT_BP, 'British Parliamentary (BP)'),
        (FORMAT_WSDC, 'World Schools (WSDC)'),
        (FORMAT_PS, 'Public Speaking'),
    ]

    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50, blank=True)
    slug = models.SlugField(unique=True, blank=True)
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default=FORMAT_BP)
    tab_master = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tournaments')

    num_prelim_rounds = models.PositiveIntegerField(null=True, blank=True)
    current_round_seq = models.PositiveIntegerField(default=0)

    speaker_score_min = models.PositiveIntegerField(default=50)
    speaker_score_max = models.PositiveIntegerField(default=100)
    reply_score_min = models.PositiveIntegerField(default=30)
    reply_score_max = models.PositiveIntegerField(default=40)
    wsdc_content_weight = models.PositiveIntegerField(default=40)
    wsdc_style_weight = models.PositiveIntegerField(default=40)
    wsdc_strategy_weight = models.PositiveIntegerField(default=20)
    # Public Speaking scoring
    ps_score_min = models.PositiveIntegerField(default=0)
    ps_score_max = models.PositiveIntegerField(default=100)
    ps_delivery_weight = models.PositiveIntegerField(default=25)
    ps_content_weight = models.PositiveIntegerField(default=25)
    ps_structure_weight = models.PositiveIntegerField(default=25)
    ps_language_weight = models.PositiveIntegerField(default=25)

    active = models.BooleanField(default=True)
    public_tab_released = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            n = 1
            while Tournament.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        if not self.short_name:
            self.short_name = self.name[:50]
        super().save(*args, **kwargs)

    def get_current_round(self):
        return self.rounds.filter(seq=self.current_round_seq).first()

    def teams_per_room(self):
        return 4 if self.format == self.FORMAT_BP else 2

    @property
    def is_bp(self):
        return self.format == self.FORMAT_BP

    @property
    def is_wsdc(self):
        return self.format == self.FORMAT_WSDC

    @property
    def is_ps(self):
        return self.format == self.FORMAT_PS


class Round(models.Model):
    DRAW_RANDOM = 'R'
    DRAW_POWER = 'P'
    DRAW_FOLD = 'F'
    DRAW_ELIMINATION = 'E'
    DRAW_CHOICES = [
        (DRAW_RANDOM, 'Random'),
        (DRAW_POWER, 'Power Paired'),
        (DRAW_FOLD, 'Fold'),
        (DRAW_ELIMINATION, 'Elimination'),
    ]

    STATUS_DRAFT = 'draft'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_RELEASED = 'released'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_RELEASED, 'Released'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='rounds')
    seq = models.PositiveIntegerField()
    name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=10, blank=True)
    draw_type = models.CharField(max_length=2, choices=DRAW_CHOICES, default=DRAW_POWER)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    is_break_round = models.BooleanField(default=False)
    silent = models.BooleanField(default=False)
    draw_released = models.BooleanField(default=False)
    results_released = models.BooleanField(default=False)
    motions_released = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('tournament', 'seq')]
        ordering = ['seq']

    def __str__(self):
        return f"{self.tournament.short_name} — {self.name}"

    def save(self, *args, **kwargs):
        if not self.abbreviation:
            self.abbreviation = f"R{self.seq}"
        super().save(*args, **kwargs)

    @property
    def is_first_round(self):
        return self.seq == 1
