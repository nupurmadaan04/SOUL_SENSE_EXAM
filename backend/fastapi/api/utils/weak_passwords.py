"""
Weak/common passwords list for server-side validation.
Passwords are stored in lowercase for case-insensitive matching.
"""

WEAK_PASSWORDS = {
    # Top most common passwords
    'password', 'password1', 'password123', 'password1234', 'password12345',
    '12345678', '123456789', '1234567890', '12345678910',
    'qwerty123', 'qwertyuiop', 'qwerty1234',
    'abc12345', 'abcdefgh', 'abc123456', 'abcd1234',
    'letmein1', 'welcome1', 'welcome123', 'monkey123',
    'dragon123', 'master123', 'login123', 'princess1',
    'football1', 'baseball1', 'soccer123', 'hockey123',
    'shadow123', 'sunshine1', 'trustno1', 'iloveyou1',
    'batman123', 'superman1', 'michael1', 'jennifer1',
    'charlie1', 'thomas123', 'jordan123', 'hunter123',
    'ranger123', 'buster123', 'killer123', 'george123',
    'robert123', 'andrea123', 'andrew123', 'joshua123',
    'matthew1', 'daniel123', 'hannah123', 'jessica1',
    'asdfghjk', 'asdf1234', 'zxcvbnm1', '1q2w3e4r',
    'qazwsx123', '1qaz2wsx', 'pass1234', 'test1234',
    'admin123', 'root1234', 'user1234', 'guest1234',
    'changeme1', 'default1', 'temp1234', 'nothing1',
    'whatever1', 'blahblah1', 'fuckyou1',
    'p@ssword1', 'p@ssw0rd', 'pa$$word1', 'passw0rd1',
    'summer123', 'winter123', 'spring123', 'autumn123',
    'january1', 'monday123', 'friday123',
    'computer1', 'internet1', 'samsung1', 'google123',
    'youtube1', 'facebook1', 'twitter1',
    'soulsense', 'soulsense1', 'soulsense123',
    'iloveyou', 'trustno1', 'access14',
    '!@#$%^&*', 'aa123456', 'aa12345678',
}
