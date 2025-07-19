from random import randint as ri 

def loop_piles(pool_size,loops):
    piles = []
    while pool_size > 0:
        pile = ri(1,pool_size)
        piles.append(pile)
        pool_size -= pile
    
    for i in range(loops):
        print(f"\nStarting loop {i+1} with {len(piles)} piles:\n{piles}")
        for j in range(len(piles)):
            piles[j]-=1 
        new_pile = len(piles)
        piles.append(new_pile)
        print(f"Added {len(piles)-1} token pile: ")
        print(piles)
        print("Removing empty piles")
        while 0 in piles:
            piles.remove(0)
            print(piles)

print(loop_piles(15,10))


        
