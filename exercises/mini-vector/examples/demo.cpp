#include "MiniVector.hpp"
#include <iostream>

// [Implementation 6] Print size and capacity changes

int main() {
    MiniVector<int> values;
    for (int i = 0; i < 8; ++i) {
        values.push_back(i * 10);
        std::cout << "size=" << values.size()
                  << " capacity=" << values.capacity() << '\n';
    }
}
