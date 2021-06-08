import random
locationlist = [[13.729085,100.775741,"ECC Building",7,"ECC-704"],[13.72794,100.74748,"Airport Rail Link Lat Krabang",2,"-"],[13.7462,100.5347,"SIAM Paragon",2,"SP-321"]]

random.seed()
choose = random.randrange(0,len(locationlist),1)
print(choose)
for i in range(5):
  print(i)
  print("Data: ", locationlist[choose][i])