      subroutine hypblue(iwa)
      real s,wlinf,wlsup
      common /sixs_ffu/ s(1501),wlinf,wlsup
      real sr(2,1501),wli(2),wls(2)
      integer iwa,l,i
c
c band 3 of MODIS (vegetation monitoring at 500m / MVI)
c
      DATA (SR(1,L),L=1,1501)/  75*0.,
     A0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000,
     A0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000,
     A0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000,
     A0.0000, 0.0007, 0.0002, 0.0001, 0.0001, 0.0001,
     A0.0001, 0.0001,
     A1400*0./
c
c    1st spectral band of enhanced thematic mapper
c
      data (sr(2,l),l=1,1501)/  74*0.,
     a .0000, .0000, .0000, .0000, .0000, .0000, .0000, .0000,
     a .0000, .0000, .0000, .0000, .0000, .0000, .0000, .0000,
     a .0000, .0000, .0000, .0000, .9800, .9770, .9650, .9628,
     a .9950, .9895, .9900, .9791, .9830, .9691, .9600, .7768,
     a .2930, .0510, .0090,	
     a1392*0./
c
C
      wli(1)=0.4375
      wls(1)=0.500
      wli(2)=0.435
      wls(2)=0.52
      do 1 i=1,1501
      s(i)=sr(iwa,i)
    1 continue
      wlinf=wli(iwa)
      wlsup=wls(iwa)
      return
      end
