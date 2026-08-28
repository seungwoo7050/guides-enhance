# 32비트 순환과 r0 불변식을 확인합니다.
li r1, 0x7fffffff
addi r1, r1, 1
li r0, 99
halt
