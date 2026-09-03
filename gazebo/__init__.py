"""Gazebo (gz sim Harmonic) kontrollu senaryo uretimi ve kayit araclari.

DIKKAT - klasor adi neden `gz` DEGIL:
Sistemde kurulu Gazebo Python baglayicilari `gz.transport13` / `gz.msgs10`
adlarini kullaniyor. Proje kokunde `gz/` adli bir paket olsaydi, betikler
proje kokunden calistirildiginda ('' sys.path'in basinda) bu paket sistem
`gz` paketini GOLGELERDI ve `import gz.transport13` sessizce kirilirdi.
Bu yuzden klasor `gazebo/`.
"""
