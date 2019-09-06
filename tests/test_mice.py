import race


def test_get_mice():
    mice = race.get_mice()
    assert len(mice)


if __name__ == '__main__':
    test_get_mice()