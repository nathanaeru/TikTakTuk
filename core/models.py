from django.db import models

class Venue(models.Model):
    nama_venue = models.CharField(max_length=255)

    def __str__(self):
        return self.nama_venue

class Seat(models.Model):
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    section = models.CharField(max_length=50) # cth: WVIP
    row = models.CharField(max_length=10)     # cth: A
    seat_number = models.IntegerField()       # cth: 1

    class Meta:
        # Sesuai instruksi: kombinasi ini harus unik
        unique_together = ('venue', 'section', 'row', 'seat_number')

    def __str__(self):
        return f"{self.section} - {self.row}{self.seat_number}"

# Tabel relasi untuk cek status terisi/kosong
class HasRelationship(models.Model):
    seat = models.OneToOneField(Seat, on_delete=models.CASCADE)
    ticket_id = models.CharField(max_length=50) # Identifikasi ke tiket